"""Finite native TEST099 runs with durable, verified opt-in handoffs."""
from pathlib import Path
import uuid
import re

from . import cycle_publication as publication
from . import native_cycle as cycle
from .test069 import _digest
from .trial_evidence099 import bundle, inspect_run
from .validation import ProbeError

MAX_RUNS = 128
LEDGER_KEYS = frozenset(('schema','campaign_id','revision','mode','state','stop_reason',
                         'runs','intent','pending_run_id','complete','pending_publication','pending_archive'))
ROW_KEYS = frozenset(('run_id','archive_name','archive_sha256','archive_bytes','outcome',
    'assessment_adopted','stop_reason','handoff','controller_reason','restarts','moves'))


def _validate(value):
    cycle.closed(value,LEDGER_KEYS,'campaign_ledger_invalid')
    cycle.require(value['schema']=='necroprobe-campaign099-v1' and cycle.identifier(value['campaign_id'])
        and type(value['revision']) is int and 0 <= value['revision'] < 2**63
        and type(value['complete']) is bool and type(value['pending_publication']) is bool
        and (not value['complete'] or value['state']=='stopped')
        and value['mode'] in ('single','until_target') and value['state'] in ('running','pending','stopped')
        and (value['stop_reason'] is None or type(value['stop_reason']) is str and len(value['stop_reason'])<=64)
        and (value['pending_run_id'] is None or cycle.identifier(value['pending_run_id']))
        and type(value['runs']) is list and len(value['runs'])<=MAX_RUNS,'campaign_ledger_invalid')
    ids=[]
    for row in value['runs']:
        cycle.closed(row,ROW_KEYS,'campaign_ledger_invalid')
        cycle.require(cycle.identifier(row['run_id']) and row['run_id'] not in ids
            and row['archive_name']=='test-099-'+row['run_id']+'.zip' and cycle.digest(row['archive_sha256'])
            and type(row['archive_bytes']) is int and 0 < row['archive_bytes'] <= 100*1024*1024
            and row['outcome'] in ('target','candidate','negative','unknown','unassessed')
            and type(row['assessment_adopted']) is bool and type(row['stop_reason']) is str
            and len(row['stop_reason'])<=64 and (row['handoff'] is None or type(row['handoff']) is dict)
            and all(cycle.ns(row[k]) for k in ('controller_reason','restarts','moves')),
            'campaign_ledger_invalid')
        ids.append(row['run_id'])
    pending=value['pending_archive']
    if pending is not None:
        cycle.closed(pending,('run_id','archive_name','archive_sha256','archive_bytes'),'campaign_ledger_invalid')
        cycle.require(pending['run_id']==value['pending_run_id'] and cycle.identifier(pending['run_id'])
            and pending['archive_name']=='test-099-'+pending['run_id']+'.zip'
            and cycle.digest(pending['archive_sha256']) and type(pending['archive_bytes']) is int
            and 0 < pending['archive_bytes'] <= 100*1024*1024,'campaign_ledger_invalid')
    intent=value['intent']
    if intent is not None:
        cycle.closed(intent,('kind','after_run_id'),'campaign_ledger_invalid')
        cycle.require(intent['kind'] in ('explicit','handoff')
            and (intent['after_run_id'] is None or cycle.identifier(intent['after_run_id'])), 'campaign_ledger_invalid')
        if intent['kind']=='handoff':
            cycle.require(value['runs'] and intent['after_run_id']==value['runs'][-1]['run_id']
                and value['runs'][-1]['stop_reason']=='handoff','campaign_ledger_invalid')
    return value


def _save(base,ledger):
    _validate(ledger)
    history=Path(base)/'campaigns';history.mkdir(mode=0o700,exist_ok=True)
    cycle.require(not history.is_symlink(),'cycle_local_symlink')
    ledger['revision']+=1
    raw=cycle.canonical(ledger)
    cycle._atomic(history/(ledger['campaign_id']+'.json'),raw)
    cycle._atomic(Path(base)/'campaign.json',raw)


def _load(base):
    active=Path(base)/'campaign.json'
    if not active.exists():return None
    selector=_validate(cycle.json_object(cycle._read(active,512*1024),512*1024))
    path=Path(base)/'campaigns'/(selector['campaign_id']+'.json')
    ledger=_validate(cycle.json_object(cycle._read(path,512*1024),512*1024))
    cycle.require(ledger['campaign_id']==selector['campaign_id']
        and ledger['revision']>=selector['revision'],'campaign_ledger_invalid')
    return ledger


def _new(until_target):
    return dict(schema='necroprobe-campaign099-v1',campaign_id=uuid.uuid4().hex,revision=0,
        mode='until_target' if until_target else 'single',state='running',stop_reason=None,
        runs=[],intent=None,pending_run_id=None,complete=False,pending_publication=False,pending_archive=None)


def _row(base,record,archive):
    evidence=inspect_run(base,record)
    count,digest=_digest(Path(archive),lambda:False)
    cycle.require(digest==record['archive_sha256'],'campaign_archive_changed')
    return dict(run_id=record['run_id'],archive_name='test-099-'+record['run_id']+'.zip',
                archive_sha256=digest,archive_bytes=count,**evidence)


def _bind(base,ledger,record,archive):
    row=_row(base,record,archive)
    known=[old for old in ledger['runs'] if old['run_id']==record['run_id']]
    if known:
        cycle.require(known==[ledger['runs'][-1]] and known[0]==row,'campaign_run_changed')
        if ledger['pending_run_id'] is not None or ledger['pending_archive'] is not None or ledger['pending_publication']:
            ledger.update(pending_run_id=None,pending_archive=None,pending_publication=False,complete=False)
            _save(base,ledger)
        return row
    intent=ledger['intent']
    cycle.require(not ledger['runs'] or intent is not None,'campaign_unexpected_run')
    if intent is not None and ledger['runs']:
        cycle.require(intent['after_run_id']==ledger['runs'][-1]['run_id'],'campaign_intent_changed')
        cycle.require(record['run_id']!=intent['after_run_id'],'campaign_run_changed')
    cycle.require(len(ledger['runs'])<MAX_RUNS,'campaign_run_limit')
    ledger['runs'].append(row);ledger.update(intent=None,pending_run_id=None,state='running',stop_reason=None,
        pending_archive=None,pending_publication=False,complete=False)
    _save(base,ledger)
    return row


def _verify_predecessor(base,ledger):
    last=ledger['runs'][-1]
    folder=Path(base)/('cycle-'+last['run_id'])
    cycle.require(not folder.is_symlink() and not (folder/'records').is_symlink(),'cycle_local_symlink')
    old=cycle.json_object(cycle._read(folder/'journal.json',512*1024),512*1024)
    cycle.require(old.get('run_id')==last['run_id'] and old.get('published') is True
                  and old.get('resolved') is True,'campaign_unpublished_run')
    row=_row(base,old,_last_archive(base,ledger))
    cycle.require(row==last and row['stop_reason']=='handoff','campaign_run_changed')


def _last_archive(base,ledger):
    last=ledger['pending_archive'] or (ledger['runs'][-1] if ledger['runs'] else None)
    if last is None:return None
    return Path(base).parent/('.'+Path(base).name+'-publication')/(last['run_id']+'.zip')


def _result(base,destination,ledger,record,archive,reason,*,pending=False):
    state='pending' if pending else 'stopped'
    complete=bool(not pending and ledger['runs'] and not ledger['pending_run_id'])
    if ledger['state']!=state or ledger['stop_reason']!=reason or ledger['complete']!=complete:
        ledger.update(state=state,stop_reason=reason,complete=complete)
        _save(base,ledger)
    final=(bundle(destination,ledger,_last_archive(base,ledger))
           if not pending or ledger['pending_archive'] is not None else None)
    return dict(record=record,archive=archive,campaign_archive=final,ledger=ledger,stop_reason=reason)


def _publish(client,destination,base,*,recovery_only=False,cancelled,notice):
    try:
        record,archive=publication.run(client,destination,spool=base,recovery_only=recovery_only,
            cancelled=cancelled,notice=notice)
        return record,archive,None
    except ProbeError as error:
        record=cycle.load_journal(base)
        if record is None:raise
        code=error.code if re.fullmatch('[a-z_0-9]{1,64}',error.code) else 'campaign_publication_failed'
        return record,None,code


def _pending(base,destination,ledger,record,error):
    reason=error or record['last_error'] or 'pending'
    descriptor=None
    if record['resolved'] and cycle.digest(record.get('archive_sha256')):
        path=Path(base).parent/('.'+Path(base).name+'-publication')/(record['run_id']+'.zip')
        try:
            cycle.require(not path.is_symlink(),'cycle_local_symlink')
            size,digest=_digest(path,lambda:False)
            if digest==record['archive_sha256']:
                descriptor=dict(run_id=record['run_id'],archive_name='test-099-'+record['run_id']+'.zip',
                    archive_sha256=digest,archive_bytes=size)
        except (OSError,ProbeError):pass
    ledger.update(pending_run_id=record['run_id'],pending_archive=descriptor,
        pending_publication=error is not None,complete=False,state='pending',stop_reason=reason)
    _save(base,ledger)
    return _result(base,destination,ledger,record,None,reason,pending=True)


def run(client,destination,*,spool,until_target=False,recovery_only=False,
        cancelled=lambda:False,notice=print):
    """Opt-in automatic *new* starts follow only validated immutable C proofs.

    A start intent is durable before normal publication is entered. On retry,
    the active native journal distinguishes an unstarted local attempt from an
    already started/uncertain run; that run is recovered, never skipped.
    """
    cycle.require(not (until_target and recovery_only),'campaign_mode_conflict')
    base=Path(spool);base.mkdir(mode=0o700,parents=True,exist_ok=True)
    cycle.require(not base.is_symlink(),'cycle_local_symlink')
    lock=base/'campaign.lock';cycle.require(not lock.is_symlink(),'cycle_local_symlink')
    with cycle.device_lock(lock):
        ledger=_load(base);active=cycle.load_journal(base)
        if recovery_only:
            cycle.require(active is not None and active['start_intent'],'cycle_recovery_record_missing')
        # An explicit new invocation may start a new campaign after a completed
        # one, but its published predecessor must be reconciled first.
        explicit_after=None;already_reconciled=False
        if ledger is not None and ledger['state']=='stopped' and not recovery_only:
            cycle.require(active is not None and active['published'],'campaign_active_missing')
            old,old_zip,error=_publish(client,destination,base,recovery_only=True,cancelled=cancelled,notice=notice)
            if old_zip is None:return _pending(base,destination,ledger,old,error)
            _bind(base,ledger,old,old_zip)
            explicit_after=old['run_id'];already_reconciled=True;ledger=None
        if ledger is None:
            ledger=_new(until_target);_save(base,ledger)
        if already_reconciled:
            ledger['intent']=dict(kind='explicit',after_run_id=explicit_after);_save(base,ledger)
        record=active;archive=None;row=None
        if active is not None and active['start_intent'] and not already_reconciled:
            record,archive,error=_publish(client,destination,base,recovery_only=True,cancelled=cancelled,notice=notice)
            if archive is None:return _pending(base,destination,ledger,record,error)
            row=_bind(base,ledger,record,archive)
            if recovery_only:
                reason=ledger['stop_reason'] if ledger['state']=='stopped' else row['stop_reason']
                if reason=='handoff':reason='recovery'
                return _result(base,destination,ledger,record,archive,reason)
        elif active is None and ledger['runs']:
            return _result(base,destination,ledger,record,None,'campaign_active_missing',pending=True)
        while True:
            if cancelled():return _result(base,destination,ledger,record,archive,'cancelled')
            if row is not None:
                reason=row['stop_reason']
                if reason!='handoff':return _result(base,destination,ledger,record,archive,reason)
                if not until_target:return _result(base,destination,ledger,record,archive,'single')
                if len(ledger['runs'])>=MAX_RUNS:
                    return _result(base,destination,ledger,record,archive,'campaign_run_limit')
                notice('正常な区切りの全記録を保存しました。次の有限runへ進みます。')
                ledger['intent']=dict(kind='handoff',after_run_id=row['run_id'])
                ledger.update(state='running',stop_reason=None);_save(base,ledger)
            elif ledger['intent'] is None:
                ledger['intent']=dict(kind='explicit',after_run_id=active['run_id'] if active and active['published'] else None)
                _save(base,ledger)
            # A resumed next-intent must still name the active published
            # predecessor, or the new unstarted journal created by that intent.
            current=cycle.load_journal(base);intent=ledger['intent']
            if current is not None and current['published']:
                cycle.require(current['run_id']==intent['after_run_id'],'campaign_intent_changed')
            elif current is not None and current['start_intent']:
                raise ProbeError('campaign_unreconciled_run')
            if intent['kind']=='handoff':_verify_predecessor(base,ledger)
            record,archive,error=_publish(client,destination,base,cancelled=cancelled,notice=notice)
            if archive is None:return _pending(base,destination,ledger,record,error)
            row=_bind(base,ledger,record,archive)
