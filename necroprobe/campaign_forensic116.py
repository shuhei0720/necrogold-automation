"""Read-only closure for one linked, unstarted final campaign attempt."""
import hashlib
import re
from pathlib import Path

from . import native_cycle as cycle
from .test069 import _digest


RESERVATION_KEYS = frozenset(('schema','root_id','run_id','index','predecessor_id','token_id','slot_bytes'))
STOPS = frozenset(('cancelled','owner','locked','storage','session','native_limit'))
COLLECTION_SCOPE = dict(scope='manifest_files_and_artifact_inventory',
    opaque_uncommitted_bytes='device_retained_not_transferred')


def verify_publication(base, record, row=None):
    """A local Boolean cannot replace the durable ZIP and native receipt."""
    invalid='cycle_publication_receipt'
    needed={'run_id','resolved','published','start_intent','schema','revision','profile',
        'export_id','manifest_sha256','archive_sha256'}
    cycle.require(type(record) is dict and needed<=set(record)
        and record['resolved'] is True and record['published'] is True and record['start_intent'] is True
        and record['schema']=='ngg2-cycle-client-v1' and record['revision']==cycle.IRREGULAR_PROTOCOL.revision
        and record['profile']==cycle.IRREGULAR_PROTOCOL.profile and cycle.identifier(record['run_id'])
        and cycle.identifier(record['export_id']) and cycle.digest(record['manifest_sha256'])
        and cycle.digest(record['archive_sha256']),invalid)
    storage=Path(base).parent/('.'+Path(base).name+'-publication')
    receipt=cycle.json_object(cycle._read(storage/(record['run_id']+'.receipt.json'),4096),4096)
    cycle.closed(receipt,('schema','run_id','export_id','manifest_sha256','archive_sha256','archive_bytes','receipt_sha256'),invalid)
    cycle.require(receipt['schema']=='ngg2-cycle-publication-v1' and receipt['run_id']==record['run_id']
        and receipt['export_id']==record['export_id'] and receipt['manifest_sha256']==record['manifest_sha256']
        and receipt['archive_sha256']==record['archive_sha256'] and cycle.digest(receipt['receipt_sha256'])
        and type(receipt['archive_bytes']) is int and 0<receipt['archive_bytes']<=100*1024*1024,invalid)
    archive=storage/(record['run_id']+'.zip')
    cycle.require(not archive.is_symlink()
        and _digest(archive,lambda:False)==(receipt['archive_bytes'],receipt['archive_sha256']),'cycle_archive_changed')
    if row is not None:
        cycle.require(row['archive_bytes']==receipt['archive_bytes']
            and row['archive_sha256']==receipt['archive_sha256'],'campaign_archive_changed')


def verify_closed_collection(base, ledger):
    cycle.require(ledger['collection_complete'],'campaign_collection_pending')
    for row in ledger['runs']:
        path=Path(base)/('cycle-'+row['run_id'])/'journal.json'
        record=cycle.json_object(cycle._read(path,512*1024),512*1024)
        cycle.require(record.get('run_id')==row['run_id'] and record.get('profile')==cycle.IRREGULAR_PROTOCOL.profile,
                      'cycle_journal_invalid')
        verify_publication(base,record,row)


def admit(base, record, native, descriptor, collected, *, index_source):
    """Verify evidence for collection only; never construct a game terminal."""
    from . import campaign116 as campaign
    invalid='campaign_orphan_unqualified'
    cycle.require(native is not None and index_source=='live' and native['state']=='stopped'
        and native['terminal'] and native['workers_drained'] and native['input_state']==4
        and native['ui_frozen'] and not native['native_inflight'] and native['stop_reason'] in STOPS
        and descriptor==native['children'][-1] and descriptor['index']>0
        and descriptor['state']=='stopped' and not descriptor['escrow_sealed']
        and descriptor['escrow_sha256'] is None and descriptor['terminal_reason'] in (2,3,4,5,6,15,19),invalid)
    parent=native['children'][-2]
    cycle.require(descriptor['predecessor_id']==parent['run_id']
        and descriptor['index']==parent['index']+1 and parent['run_id'] in collected,invalid)
    parent_record=collected[parent['run_id']][0]
    verify_publication(base,parent_record)
    parent_manifest=campaign._stored_manifest(base,parent_record)
    cycle.require(parent_manifest['complete'] and not parent_manifest['interrupted']
        and not parent_manifest['diagnostics'],invalid)
    campaign.verify_child(base,parent_record,native,parent)
    parent_seal_item,parent_seal=campaign._record_body(base,parent_record,'continuation_seal')
    payload=parent_seal['payload']
    cycle.require(payload['next_run_id']==record['run_id']==descriptor['run_id']
        and payload['controller']['qualified'] is True,invalid)
    restart_sequences=[]
    for item in parent_record['records']:
        if item['kind']!='restart_intent':continue
        path=Path(base)/('cycle-'+parent_record['run_id'])/'records'/cycle.record_name(item)
        intent=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD).get('payload',{})
        command=intent.get('command') if type(intent) is dict else None
        cycle.require(type(command) is dict,invalid)
        if command.get('id')==payload['controller']['restart_command_id']:
            restart_sequences.append(item['sequence'])
    cycle.require(len(restart_sequences)==1,invalid)
    reservations=[]
    for item in parent_record['records']:
        if item['kind']!='continuation_reservation':continue
        path=Path(base)/('cycle-'+parent_record['run_id'])/'records'/cycle.record_name(item)
        body=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)
        p=body.get('payload');cycle.closed(p,RESERVATION_KEYS,invalid)
        cycle.require(p['schema']=='ngg2-continuation-reservation-v1'
            and cycle.identifier(p['token_id']) and type(p['slot_bytes']) is int
            and p['slot_bytes']==156*1024*1024,invalid)
        if p['run_id']==record['run_id']:
            cycle.require(p['root_id']==native['root_id'] and type(p['index']) is int
                and p['index']==descriptor['index'] and p['predecessor_id']==parent['run_id']
                and item['sequence']<restart_sequences[0]<parent_seal_item['sequence'],invalid)
            reservations.append(item)
    cycle.require(len(reservations)==1,invalid)
    verify_publication(base,record)
    manifest=campaign._stored_manifest(base,record)
    cycle.require(not manifest['complete'] and manifest['interrupted'] and manifest['terminal']
        and manifest['workers_drained'] and manifest['input_state']==4 and manifest['ui_frozen']
        and not manifest['native_inflight'] and not manifest['images']
        and all(r['kind'] in ('session','artifacts') for r in record['records']),invalid)
    for diagnostic in manifest['diagnostics']:
        cycle.require(type(diagnostic) is dict,invalid)
        code=diagnostic.get('code')
        extra=('count',) if code=='interrupted_artifacts' else ()
        cycle.closed(diagnostic,('code','authority')+extra,invalid)
        cycle.require(code in ('session_header_uncommitted','original_export_integrity_or_storage','interrupted_artifacts')
            and diagnostic['authority'] is False,invalid)
        if extra:cycle.require(cycle.ns(diagnostic['count']) and diagnostic['count']<=1024,invalid)
    headers=[r for r in record['records'] if r['kind']=='session']
    if headers:
        child_header=campaign._header(base,record)
        cycle.require(child_header['root_id']==native['root_id']
            and child_header['index']==descriptor['index']
            and child_header['predecessor_id']==parent['run_id']
            and child_header['root_deadline_ns']==native['deadline_ns'],invalid)
        _parent_item,parent_header=campaign._record_body(base,parent_record,'session')
        _child_item,child_session=campaign._record_body(base,record,'session')
        provenance=child_session.get('provenance',{})
        cycle.require(cycle.digest(parent_header.get('owner_sha256'))
            and child_session.get('owner_sha256')==parent_header['owner_sha256']
            and type(provenance) is dict and provenance.get('native_profile')==cycle.IRREGULAR_PROTOCOL.profile
            and cycle.identifier(provenance.get('clock_id')) and cycle.ns(provenance.get('generation'))
            and provenance['generation']>0 and cycle.ns(provenance.get('accepted_started_ns'))
            and payload['controller']['qualified_ns']<=provenance['accepted_started_ns']<native['deadline_ns'],invalid)
    else:
        cycle.require(any(d.get('code')=='session_header_uncommitted' and d.get('authority') is False
            for d in manifest['diagnostics'] if type(d) is dict),invalid)
    inventories=[r for r in record['records'] if r['kind']=='artifacts']
    cycle.require(len(inventories)<=1 and all(r['sequence']==557 for r in inventories),invalid)
    for item in inventories:
        path=Path(base)/('cycle-'+record['run_id'])/'records'/cycle.record_name(item)
        inventory=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)
        cycle.closed(inventory,('schema','run_id','artifacts'),invalid)
        cycle.require(inventory['schema']=='ngg2-cycle-artifacts-v1' and inventory['run_id']==record['run_id']
            and type(inventory['artifacts']) is list and len(inventory['artifacts'])<=1024,invalid)
        for artifact in inventory['artifacts']:
            cycle.closed(artifact,('id','name','kind','bytes','sha256','authority'),invalid)
            name=artifact['name']
            cycle.require(type(name) is str and (name=='session.json' or re.fullmatch(
                r'\.part-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',name))
                and artifact['id']==hashlib.sha256(name.encode()).hexdigest()
                and artifact['kind'] in ('metadata','uncommitted') and artifact['authority'] is False
                and cycle.ns(artifact['bytes']) and artifact['bytes']<=2*1024*1024
                and cycle.digest(artifact['sha256']),invalid)
    return dict(outcome='unknown',assessment_adopted=False,stop_reason='prepared_child_diagnostic',
        controller_reason=0,restarts=0,moves=0)
