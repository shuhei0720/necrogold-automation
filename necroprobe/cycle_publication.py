"""Publish TEST094's immutable complete session, then acknowledge its hash."""
import hashlib
from pathlib import Path
import zipfile

from . import native_cycle as cycle
from .native_walk import _atomic
from .test069 import _copy, _digest, _sync_directory


def _inventory(base, record, cancelled):
    manifest = cycle.verify_evidence(base, record)
    folder = base/('cycle-'+record['run_id'])
    snapshot = folder/'archive-journal.json'
    if not snapshot.exists():
        _atomic(snapshot, cycle.canonical(record))
    source = cycle.json_object(cycle._read(snapshot, 512*1024), 512*1024)
    cycle.require(source['run_id'] == record['run_id']
        and source['manifest_sha256'] == record['manifest_sha256']
        and source['export_id'] == record['export_id'] and source['resolved']
        and source['images'] == record['images'] and source['records'] == record['records'],
        'cycle_archive_snapshot_changed')
    paths = [snapshot, folder/'native-manifest.json']
    paths += [folder/'records'/cycle.record_name(item) for item in manifest['records']]
    paths += [folder/'images'/item['name'] for item in manifest['images']]
    # The inventory is derived only from the immutable native registry, never
    # an unbounded rglob that could admit a private or unrelated file.
    return [(('test-094/'+path.relative_to(base).as_posix()), path,
             *_digest(path, cancelled)) for path in paths]


def _verify(path, inventory, cancelled):
    cycle.require(not path.is_symlink(), 'cycle_local_symlink')
    with zipfile.ZipFile(path) as archive:
        cycle.require(archive.namelist() == [row[0] for row in inventory], 'cycle_archive_inventory')
        for name, _source, size, digest in inventory:
            cycle.require(not cancelled(), 'cancel_requested')
            info = archive.getinfo(name)
            cycle.require(info.file_size == size and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                          'cycle_archive_inventory')
            sha = hashlib.sha256()
            count = 0
            with archive.open(info) as entry:
                while True:
                    cycle.require(not cancelled(), 'cancel_requested')
                    raw = entry.read(256*1024)
                    if not raw:
                        break
                    count += len(raw)
                    sha.update(raw)
            cycle.require((count, sha.hexdigest()) == (size, digest), 'cycle_archive_changed')


def build_archive(base, record, storage, *, cancelled=lambda: False):
    cycle.require(record['resolved'], 'cycle_files_incomplete')
    inventory = _inventory(base, record, cancelled)
    archive = storage/(record['run_id']+'.zip')
    if archive.exists():
        _verify(archive, inventory, cancelled)
        return archive
    temporary = storage/(record['run_id']+'.zip.building')
    cycle.require(not temporary.is_symlink(), 'cycle_local_symlink')
    with temporary.open('wb') as target:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as result:
            for name, source, _size, _sha in inventory:
                cycle.require(not cancelled(), 'cancel_requested')
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info._compresslevel = 6
                info.external_attr = 0o600 << 16
                with source.open('rb') as original, result.open(info, 'w') as entry:
                    while True:
                        cycle.require(not cancelled(), 'cancel_requested')
                        raw = original.read(256*1024)
                        if not raw:
                            break
                        entry.write(raw)
        target.flush()
        cycle.os.fsync(target.fileno())
    _verify(temporary, inventory, cancelled)
    cycle.require(not archive.exists(), 'cycle_archive_exists')
    cycle.os.replace(temporary, archive)
    _sync_directory(storage)
    return archive


def publish(client, base, destination, record, *, cancelled=lambda: False,
            clock=cycle.time.monotonic_ns, sleep=cycle.time.sleep, notice=print):
    base, destination = Path(base), Path(destination)
    storage = base.parent/('.'+base.name+'-publication')
    storage.mkdir(mode=0o700, exist_ok=True)
    cycle.require(not storage.is_symlink(), 'cycle_local_symlink')
    notice('全画像と実行記録を照合し、返却用ZIPを保存しています。')
    source = build_archive(base, record, storage, cancelled=cancelled)
    signature = _digest(source, cancelled)
    if record['archive_sha256'] is not None:
        cycle.require(record['archive_sha256'] == signature[1], 'cycle_archive_changed')
    output = destination/'runtime'
    output.mkdir(parents=True, exist_ok=True)
    cycle.require(not output.is_symlink(), 'cycle_local_symlink')
    final = output/('test-094-'+record['run_id']+'.zip')
    if not final.exists():
        part = final.with_name(final.name+'.part')
        _copy(source, part, cancelled)
        cycle.require(_digest(part, cancelled) == signature, 'cycle_archive_copy_changed')
        cycle.require(not final.exists(), 'cycle_archive_exists')
        cycle.os.replace(part, final)
        _sync_directory(output)
    cycle.require(_digest(final, cancelled) == signature, 'cycle_archive_copy_changed')
    record['archive_sha256'] = signature[1]
    cycle._journal(base, record)
    # This is an acknowledgement of the client's durable publication.  It is
    # not a claim that the native server independently inspected ZIP bytes.
    deadline = clock()+30_000_000_000
    while not record['published']:
        cycle._checked(cancelled, clock, deadline)
        params = {'run_id':record['run_id'], 'mode':'published', 'export_id':record['export_id'],
                  'manifest_sha256':record['manifest_sha256'], 'archive_sha256':signature[1]}
        response = cycle.envelope(cycle._call(client, 'necro_native_cycle', params), record['run_id'], 'published')
        cycle.closed(response, ('accepted', 'export_id', 'manifest_sha256', 'archive_sha256', 'receipt_sha256'))
        cycle.require(type(response['accepted']) is bool and response['export_id'] == record['export_id']
            and response['manifest_sha256'] == record['manifest_sha256']
            and response['archive_sha256'] == signature[1]
            and (cycle.digest(response['receipt_sha256']) if response['accepted'] else response['receipt_sha256'] is None))
        if response['accepted']:
            receipt = dict(schema='ngg2-cycle-publication-v1', run_id=record['run_id'],
                export_id=record['export_id'], manifest_sha256=record['manifest_sha256'],
                archive_sha256=signature[1], archive_bytes=signature[0], receipt_sha256=response['receipt_sha256'])
            _atomic(storage/(record['run_id']+'.receipt.json'), cycle.canonical(receipt))
            record.update(published=True, last_error=None)
            cycle._journal(base, record)
            break
        sleep(.25)
    return final


def run(client, destination, *, spool, cancelled=lambda: False, notice=print,
        clock=cycle.time.monotonic_ns, sleep=cycle.time.sleep):
    base = Path(spool)
    base.mkdir(parents=True, mode=0o700, exist_ok=True)
    with cycle.device_lock():
        previous = cycle.load_journal(base)
        if previous is not None and previous['published']:
            # A Boolean in the active journal is not a replacement for the
            # durable archive and receipt that originally authorized it.
            storage = base.parent/('.'+base.name+'-publication')
            receipt_path = storage/(previous['run_id']+'.receipt.json')
            receipt = cycle.json_object(cycle._read(receipt_path, 4096), 4096)
            cycle.closed(receipt, ('schema', 'run_id', 'export_id', 'manifest_sha256',
                'archive_sha256', 'archive_bytes', 'receipt_sha256'))
            cycle.require(receipt['schema'] == 'ngg2-cycle-publication-v1'
                and receipt['run_id'] == previous['run_id']
                and receipt['export_id'] == previous['export_id']
                and receipt['manifest_sha256'] == previous['manifest_sha256']
                and receipt['archive_sha256'] == previous['archive_sha256']
                and cycle.digest(receipt['receipt_sha256']), 'cycle_publication_receipt')
            previous_archive = build_archive(base, previous, storage, cancelled=cancelled)
            cycle.require(_digest(previous_archive, cancelled) ==
                (receipt['archive_bytes'], receipt['archive_sha256']), 'cycle_archive_changed')
        record = cycle.run_session(client, base, cancelled=cancelled, notice=notice, clock=clock, sleep=sleep)
        if not record['resolved']:
            return record, None
        archive = publish(client, base, destination, record, cancelled=cancelled,
                          notice=notice, clock=clock, sleep=sleep)
        return record, archive
