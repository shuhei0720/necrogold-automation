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
        if method == cycle._spec(self.protocol_spec).query and type(params) is dict and params.get('mode') == 'trial_support':
            cycle.closed(params, ('run_id','mode'), 'method_not_allowed')
            cycle.require(cycle.identifier(params.get('run_id')), 'method_not_allowed')
            return
        return super()._validate(method, params)

    def check_schema(self):
        result = super().check_schema()
        try:
            reply = cycle._call(self, cycle._spec(self.protocol_spec).query,
                dict(run_id=self.trial_probe_id,mode='trial_support'))
        except ProbeError as error:
            if getattr(error,'rpc_code',None) in (-32601,-32602) and getattr(error,'error_shape_valid',False):
                raise ProbeError('trial_support_missing') from None
            raise
        payload = cycle.envelope(reply,self.trial_probe_id,'trial_support', protocol_spec=self.protocol_spec)
        cycle.closed(payload,SUPPORT,'trial_support_invalid')
        cycle.require(payload == SUPPORT and type(payload['maximum_run_ids']) is int
                      and type(payload['pin_limit']) is int, 'trial_support_invalid')
        return result


class IrregularTrialClient110(TrialClient099):
    protocol_spec = cycle.IRREGULAR_PROTOCOL


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



def _raw_assessment_hints(assessment):
    """Read bounded diagnostic hints; none of these grants input authority."""
    if type(assessment) is not dict:
        return False, assessment is not None
    rows=assessment.get('rows',[]);partial=assessment.get('partial',[])
    if type(rows) is not list or len(rows)>4 or type(partial) is not list or len(partial)>12:
        return False, True
    positive=False;invalid=False;slots=list(partial)
    for row in rows:
        if type(row) is not dict:
            invalid=True;continue
        outcome=row.get('outcome')
        positive=positive or outcome in ('target','candidate')
        invalid=invalid or outcome not in ('unknown','target','candidate','negative')
        items=row.get('slots',[])
        if type(items) is not list or len(items)>3:
            invalid=True
        else:
            slots.extend(items)
    for slot in slots:
        if type(slot) is not dict:
            invalid=True;continue
        outcome=slot.get('outcome')
        positive=positive or outcome in ('target','candidate')
        invalid=invalid or outcome not in ('unknown','candidate','target','non_target','ignored_container')
    return positive,invalid


def _restarted_handoff(payload, frames, checkpoints, records, session):
    """Prove a paused new floor without reusing its predecessor's negative."""
    invalid = 'campaign_handoff_invalid'
    controller = payload['controller']; state = payload['cycle']
    value = cycle.closed(controller.get('handoff'), HANDOFF_KEYS, invalid)
    cycle.require(value['schema'] == 'ngg2-trial-handoff-v1'
        and value['kind'] == 'restarted_budget' and value['allowed'] is True
        and value['reason'] == 14
        and all(cycle.ns(value[k]) for k in HANDOFF_KEYS-{'schema','kind','allowed'}), invalid)
    provenance = session.get('provenance') if type(session) is dict else None
    cycle.require(type(provenance) is dict and provenance.get('yield_after_restart') is True
        and provenance.get('native_profile') == cycle.IRREGULAR_PROTOCOL.profile
        and cycle.digest(session.get('owner_sha256')) and cycle.identifier(provenance.get('clock_id'))
        and cycle.ns(provenance.get('accepted_started_ns'))
        and cycle.ns(provenance.get('generation')) and provenance['generation'] > 0, invalid)
    numbers = ('terminal','phase','paused','input_state','current_command_id',
        'last_completed_id','reason','started_ns','walk_started_ns','ended_ns','restarts','inputs','moves','x','y')
    cycle.require(all(type(controller.get(k)) is int for k in numbers)
        and controller['terminal'] == 1 and controller['phase'] == 7 and controller['paused'] == 1
        and controller['input_state'] == controller['current_command_id'] == 0 and controller['reason'] == 14
        and controller['x'] == controller['y'] == 0
        and 1 <= controller['inputs'] <= 16 and 0 <= controller['moves'] <= controller['inputs']
        and 1 <= controller['restarts'] <= 12
        and provenance['accepted_started_ns'] <= controller['started_ns'] <= controller['walk_started_ns'] < controller['ended_ns']
        and controller['ended_ns']-controller['started_ns'] < 180_000_000_000
        and controller['ended_ns']-controller['walk_started_ns'] < 45_000_000_000
        and state.get('state') == 'done' and state.get('pending') is False
        and state.get('candidate_latched') is False and state.get('assessment_status') == 'ok'
        and state.get('outcome') in ('unknown','negative'), invalid)
    cycle.require(all(cycle.ns(state.get(k)) for k in ('job_id','level_id','capture_id',
        'capture_start_ns','prefix','worker_started_ns','assessment_ns')), invalid)
    cycle.require(all(type(r.get('payload')) is dict for r in records)
        and all(type(r['payload'].get('cycle')) is dict for r in checkpoints), invalid)
    source = _frame(frames, value['source_capture_id'], value['source_prefix'])
    pause = _frame(frames, value['pause_capture_id'], value['completed_prefix'])
    generation = provenance['generation']
    cycle.require(source['generation'] == pause['generation'] == generation
        and source['capture_id'] < pause['capture_id']
        and source['capture_end_ns'] <= value['qualified_ns'] <= controller['ended_ns']
        and pause['capture_end_ns'] <= controller['ended_ns']
        and value['source_prefix'] < value['completed_prefix'] == controller['last_completed_id'], invalid)
    events = controller.get('events')
    cycle.require(type(events) is list and len(events) <= 64
        and all(type(e) is dict and cycle.ns(e.get('id')) and e['id'] > 0 for e in events)
        and len({e['id'] for e in events}) == len(events)
        and not any(e.get('outcome') == 4 for e in events), invalid)
    restarts = [e for e in events if e.get('id') == value['source_prefix']]
    pauses = [e for e in events if e.get('id') == value['completed_prefix']]
    cycle.require(len(restarts) == len(pauses) == 1, invalid)
    restart, paused = restarts[0], pauses[0]
    event_fields = ('id','kind','outcome','source_capture_id','source_start_ns','begin_ns','end_ns','observed_capture_id')
    for event, kind in ((restart,3),(paused,2)):
        cycle.require(all(cycle.ns(event.get(k)) for k in event_fields)
            and event['kind'] == kind and event['outcome'] == 2
            and 0 < event['begin_ns'] <= event['end_ns'], invalid)
    cycle.require([e for e in events if e['id'] > restart['id']] == [paused]
        and paused['source_capture_id'] == value['source_capture_id']
        and paused['source_start_ns'] == source['capture_start_ns']
        and paused['observed_capture_id'] == value['pause_capture_id']
        and value['qualified_ns'] <= paused['begin_ns']
        and paused['end_ns'] <= pause['capture_start_ns'], invalid)
    intents = [r for r in records if r['kind'] == 'restart_intent'
        and type(r['payload'].get('command')) is dict
        and r['payload']['command'].get('id') == restart['id']]
    outcomes = [r for r in records if r['kind'] == 'restart_outcome'
        and r['payload'].get('floor_prefix') == restart['id']]
    terminals = [r for r in records if r['kind'] == 'terminal']
    cycle.require(len(intents) == len(outcomes) == len(terminals) == 1, invalid)
    intent_record, outcome_record = intents[0], outcomes[0]
    intent = cycle.closed(intent_record['payload'], ('cycle','command','generation','source_prefix','source_raw_sha256'), invalid)
    outcome = cycle.closed(outcome_record['payload'], ('cycle','generation','floor_capture_id','floor_prefix','floor_raw_sha256','controller'), invalid)
    old = intent['cycle']; after = outcome['cycle']; command = intent['command']
    cycle.require(type(old) is dict and type(after) is dict
        and intent['generation'] == outcome['generation'] == generation
        and type(intent['generation']) is int and type(outcome['generation']) is int, invalid)
    from .irregular import validate_command
    try: validate_command(command, kinds=(3,))
    except ProbeError: raise ProbeError(invalid) from None
    old_negative, negative_frame = _negative(checkpoints,old,frames)
    checkpoint_records = [r for r in checkpoints if r['payload'] is old_negative]
    cycle.require(len(checkpoint_records) == 1
        and checkpoint_records[0]['sequence'] < intent_record['sequence'] < outcome_record['sequence'] < terminals[0]['sequence']
        and old_negative.get('run_id') == session.get('run_id')
        and old_negative.get('clock_id') == provenance['clock_id']
        and type(old_negative.get('generation')) is int and old_negative['generation'] == generation
        and old.get('capture_start_ns') == negative_frame['capture_start_ns']
        and negative_frame['generation'] == generation
        and provenance['accepted_started_ns'] <= negative_frame['capture_start_ns'], invalid)
    prior = old_negative['cycle']
    identity = ('job_id','capture_id','capture_start_ns','prefix','level_id','assessment_ns')
    cycle.require(all(cycle.ns(group.get(k)) for group in (prior,old,after) for k in identity)
        and all(prior.get(k) == old[k] == after.get(k) for k in identity)
        and old['job_id'] > 0 and old['level_id'] > 0
        and cycle.ns(state.get('level_id')) and state['level_id'] == old['level_id']+1
        and after.get('durable_ns') == old.get('durable_ns')
        and cycle.ns(old.get('worker_started_ns')) and cycle.ns(old.get('deadline_ns'))
        and negative_frame['capture_end_ns'] <= old['worker_started_ns'] <= old['assessment_ns'] <= old['deadline_ns']
        and old['deadline_ns'] <= negative_frame['capture_start_ns']+150_000_000
        and old['assessment_ns']-old['worker_started_ns'] <= 100_000_000
        and old['assessment_ns'] <= old['durable_ns'] <= command['not_before_ns']
        and after.get('restart_command_id') == old.get('restart_command_id') == restart['id']
        and cycle.ns(after.get('intent_ns')) and old['durable_ns'] <= after['intent_ns'] <= restart['begin_ns']
        and after.get('outcome_ns') == 0, invalid)
    cycle.require(cycle.ns(intent['source_prefix']), invalid)
    restart_source = _frame(frames, command['source_capture_id'], intent['source_prefix'])
    cycle.require(command['id'] == restart['id'] and command['kind'] == 3
        and restart['source_capture_id'] == command['source_capture_id']
        and restart['source_start_ns'] == command['source_start_ns'] == restart_source['capture_start_ns']
        and restart_source['generation'] == generation
        and intent['source_raw_sha256'] == frames[command['source_capture_id']]['raw_sha256']
        and command['not_before_ns'] <= restart['begin_ns'] <= command['deadline_ns']
        and restart_source['capture_end_ns'] <= after['intent_ns'], invalid)
    cycle.require(all(cycle.ns(outcome[k]) for k in ('floor_capture_id','floor_prefix'))
        and cycle.ns(after.get('next_floor_capture_id')), invalid)
    first_floor = _frame(frames,outcome['floor_capture_id'],outcome['floor_prefix'])
    cycle.require(first_floor['generation'] == generation
        and restart['observed_capture_id'] == outcome['floor_capture_id'] == after.get('next_floor_capture_id')
        and outcome['floor_raw_sha256'] == frames[outcome['floor_capture_id']]['raw_sha256']
        and restart['end_ns'] <= first_floor['capture_start_ns'] <= source['capture_start_ns']
        and first_floor['capture_id'] <= source['capture_id'], invalid)
    snapshot = outcome['controller']
    cycle.require(type(snapshot) is dict and cycle.ns(snapshot.get('last_completed_id'))
        and snapshot['last_completed_id'] == restart['id']
        and all(type(snapshot.get(k)) is int and snapshot[k] == controller[k] for k in ('inputs','moves','restarts'))
        and all(type(snapshot.get(k)) is int and -(2**31) <= snapshot[k] < 2**31
                for k in ('x','y')), invalid)
    if state.get('job_id') == old['job_id']:
        # No new goods job need not erase the predecessor's diagnostic fields.
        # Runtime has removed its assessment; it is never this floor's negative.
        cycle.require(all(state.get(k) == old[k] for k in ('capture_id','capture_start_ns','prefix','assessment_ns'))
            and payload.get('assessment') is None and payload.get('assessment_adopted') is False, invalid)
    elif cycle.ns(state.get('job_id')) and state['job_id'] > old['job_id']:
        cycle.require(cycle.ns(state.get('job_id')) and state['job_id'] > old['job_id']
            and cycle.ns(state.get('capture_id')) and state['capture_id'] >= first_floor['capture_id']
            and state.get('prefix') == restart['id'] and type(payload.get('assessment')) is dict
            and payload['assessment'].get('status') == 'ok'
            and payload['assessment'].get('outcome') in ('unknown','negative'), invalid)
        data_source = _frame(frames,state['capture_id'],restart['id'])
        cycle.require(data_source['generation'] == generation
            and state.get('capture_start_ns') == data_source['capture_start_ns'], invalid)
    else:
        cycle.require(state.get('job_id') == 0 and payload.get('assessment') is None
            and all(state.get(k) == 0 for k in ('capture_id','capture_start_ns','worker_started_ns','assessment_ns'))
            and state.get('outcome') == 'unknown', invalid)
    return value,'handoff'


def inspect_run(base, record, *, protocol_spec=cycle.STANDARD_PROTOCOL, allow_restarted_budget=False):
    """Interpret only records already published and then byte-verified again."""
    cycle.require(record['resolved'] and record['published'], 'campaign_unpublished_run')
    protocol=cycle._spec(protocol_spec)
    cycle.require(type(allow_restarted_budget) is bool
        and (not allow_restarted_budget or protocol.irregular), 'cycle_protocol_invalid')
    manifest=cycle.verify_evidence(base,record,protocol_spec=protocol)
    folder=Path(base)/('cycle-'+record['run_id'])/'records'
    images={item['capture_id']:item for item in manifest['images']}
    frames={};checkpoints=[];terminals=[];positives=[];irregular_records=[];normal_records=[];sessions=[];invalid_positive_evidence=False
    for item in manifest['records']:
        raw=cycle._read(folder/cycle.record_name(item),cycle.MAX_RECORD)
        cycle.require(hashlib.sha256(raw).hexdigest()==item['sha256'],'cycle_file_changed')
        body=cycle.json_object(raw,cycle.MAX_RECORD)
        if item['kind'] not in ('session','frame'):
            if allow_restarted_budget:
                cycle.require(type(body.get('payload')) is dict,'campaign_handoff_invalid')
            normal_records.append(body)
        if allow_restarted_budget and type(body.get('payload')) is dict:
            extra=body['payload'];hint=extra.get('assessment_hint');raw_state=extra.get('cycle',{})
            assessment=extra.get('assessment')
            hinted,invalid=_raw_assessment_hints(assessment)
            invalid_positive_evidence=invalid_positive_evidence or invalid
            if hinted:
                positives.append(('candidate',False))
            if type(assessment) is dict and assessment.get('outcome') in ('target','candidate'):
                positives.append((assessment['outcome'],extra.get('assessment_adopted') is True))
            if type(hint) is dict and hint.get('outcome') in ('target','candidate'):
                positives.append(('candidate',False))
            if type(raw_state) is dict and (raw_state.get('candidate_latched') is True
                    or raw_state.get('outcome') in ('target','candidate')):
                positives.append(('candidate',False))
        if item['kind']=='session':
            sessions.append(body)
        elif item['kind']=='frame':
            image=images.get(body['capture_id'])
            if image is not None and image['raw_sha256']==body['raw_sha256']:
                frames[body['capture_id']]=body
        elif item['kind'].startswith('irregular_'):
            cycle.require(protocol.irregular, 'cycle_record_schema')
            irregular_payload=body.get('payload',{})
            irregular_records.append((item['kind'],irregular_payload))
            hint=irregular_payload.get('assessment_hint')
            if type(hint) is dict and hint.get('outcome') in ('target','candidate'):
                # A typed, source-bound hint can only hold a possible target.
                # It is not an adopted target or a completed shop assessment.
                positives.append(('candidate',False))
        elif item['kind'] in ('checkpoint','terminal','assessment'):
            payload=body.get('payload',{});assessment=payload.get('assessment')
            if type(assessment) is dict and assessment.get('outcome') in ('target','candidate'):
                positives.append((assessment['outcome'],payload.get('assessment_adopted') is True))
            if item['kind']=='checkpoint':checkpoints.append(body)
            if item['kind']=='terminal':terminals.append(payload)
    cycle.require(len(terminals)==1,'campaign_terminal_missing')
    payload=terminals[0];controller=payload.get('controller');state=payload.get('cycle')
    cycle.require(type(controller) is dict and type(state) is dict,'campaign_terminal_invalid')
    if allow_restarted_budget:
        cycle.require(cycle.ns(state.get('job_id')),'campaign_handoff_invalid')
    outcome=state.get('outcome') if state.get('job_id',0)>0 else 'unassessed'
    reason='handoff_unavailable';handoff=None
    adopted=payload.get('assessment_adopted') is True
    if positives:
        outcome='target' if any(p[0]=='target' for p in positives) else 'candidate'
        adopted=any(p[0]==outcome and p[1] for p in positives);reason=outcome
    elif record['cancel_intent']:reason='cancelled'
    elif not manifest['complete'] or manifest['interrupted'] or manifest['diagnostics']:reason='incomplete'
    elif manifest['input_state']!=0 or manifest['native_inflight'] or manifest['ui_frozen']:reason='unknown_input'
    elif invalid_positive_evidence:reason='handoff_invalid'
    elif outcome=='unknown' and not (allow_restarted_budget
        and type(controller.get('handoff')) is dict
        and controller['handoff'].get('kind')=='restarted_budget'):reason='unknown'
    elif state.get('assessment_status')!='ok':reason='assessment_failed'
    if protocol.irregular:
        from .irregular import sequence_summary
        irregular_summary=sequence_summary(irregular_records,frames)
        if not positives and irregular_summary['unknown_ack']:
            outcome='unknown';reason='unknown_input'
        elif not positives and irregular_summary['pending']:
            outcome='unknown';reason='irregular_pending'
    if reason=='handoff_unavailable':
        try:
            if (allow_restarted_budget and type(controller.get('handoff')) is dict
                    and controller['handoff'].get('kind')=='restarted_budget'):
                cycle.require(len(sessions)==1,'campaign_handoff_invalid')
                handoff,reason=_restarted_handoff(payload,frames,checkpoints,normal_records,sessions[0])
                outcome='unassessed';adopted=False
            else:
                handoff,reason=_handoff(payload,frames,checkpoints)
        except ProbeError as error:
            if error.code!='campaign_handoff_invalid':raise
            reason='handoff_invalid'
    # No assessment is not a Ring UNKNOWN, but still needs the explicit B proof.
    if outcome=='unassessed' and reason=='handoff_unavailable':reason='unassessed'
    return dict(outcome=outcome,assessment_adopted=adopted,stop_reason=reason,
        handoff=handoff,controller_reason=controller.get('reason',0),
        restarts=controller.get('restarts',0),moves=controller.get('moves',0))


def irregular_result_notice(base, record, row):
    """Report verified outcome and retry state without treating UNKNOWN as absent."""
    from .irregular import validate_status
    cycle.require(record['profile'] == cycle.IRREGULAR_PROTOCOL.profile
        and record['revision'] == cycle.IRREGULAR_PROTOCOL.revision
        and record['published'] and record['resolved'], 'cycle_journal_invalid')
    terminal=[item for item in record['records'] if item['kind']=='terminal']
    cycle.require(len(terminal)==1,'campaign_terminal_missing')
    item=terminal[0]
    raw=cycle._read(Path(base)/('cycle-'+record['run_id'])/'records'/cycle.record_name(item),cycle.MAX_RECORD)
    cycle.require(hashlib.sha256(raw).hexdigest()==item['sha256'],'cycle_file_changed')
    state=cycle.json_object(raw,cycle.MAX_RECORD).get('payload',{}).get('irregular')
    outcome=row['outcome']
    if outcome=='negative' and row['assessment_adopted']:
        assessment='完全対象なし'
    elif outcome=='target' and row['assessment_adopted']:
        assessment='のろいのゆびわ確認'
    elif outcome in ('target','candidate'):
        assessment='のろいのゆびわ候補を保持'
        if not row['assessment_adopted']:
            assessment+='（未採用の解析結果）'
    else:
        assessment='未判定' if outcome=='unassessed' else 'UNKNOWN'
    if state is None:
        detail='記録なし'
    else:
        validate_status(state)
        detail=' / '.join(state[key] for key in ('kind','stage','held_reason'))
    return '商品判定: '+assessment+'。再試行: '+detail+'。'


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
