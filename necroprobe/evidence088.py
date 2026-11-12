"""Export certified saved TEST088 evidence without assessing or starting a game."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import uuid
import zipfile

from . import native_walk as native
from . import test069 as publication


def _safe(path):
    publication._require(not any(p.is_symlink() for p in (path, *path.parents)),
                         'evidence_symlink')


def _members(base, record):
    folder = base/('native-'+record['run_id'])
    paths = [base/'active.json', folder/'report.json']
    paths.extend(folder/'images'/item['name'] for item in sorted(record['images'], key=lambda row: row['name']))
    for path in paths:
        _safe(path)
        publication._require(path.is_file(), 'evidence_source_missing')
    return paths


def _receipt(path, record):
    _safe(path)
    if not path.exists():
        return None
    publication._require(path.is_file(), 'evidence_receipt_invalid')
    with path.open('rb') as handle:
        value = native.json_object(handle.read(4097), 4096)
    publication._require(set(value) == {'schema', 'run_id', 'report_sha256', 'archive_bytes', 'archive_sha256'}
        and value['schema'] == 'ngg2-evidence-088-v1' and value['run_id'] == record['run_id']
        and type(value['archive_bytes']) is int and value['archive_bytes'] > 0
        and all(type(value[key]) is str and re.fullmatch(r'[0-9a-f]{64}', value[key])
                for key in ('report_sha256', 'archive_sha256')), 'evidence_receipt_invalid')
    return value


def _install(temporary, final):
    _safe(final)
    publication._require(not final.exists(), 'evidence_destination_exists')
    os.replace(temporary, final)
    publication._sync_directory(final.parent)


def _archive(path, inventory, cancelled):
    _safe(path)
    if path.exists():
        publication._require(path.is_file(), 'evidence_archive_invalid')
        publication._verify_archive(path, inventory, cancelled)
        return
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.building')
    try:
        with temporary.open('xb') as target:
            with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
                for name, source, _size, _digest in inventory:
                    info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
                    info.compress_type = zipfile.ZIP_STORED
                    info.external_attr = 0o600 << 16
                    with source.open('rb') as original, archive.open(info, 'w') as entry:
                        while True:
                            publication._check(cancelled)
                            chunk = original.read(256*1024)
                            if not chunk:
                                break
                            entry.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        publication._verify_archive(temporary, inventory, cancelled)
        publication._check(cancelled)
        _install(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run(destination, *, cancelled=lambda: False, notice=print):
    base = Path.home()/'.necroprobe/runtime/test-088'
    lock = base.parent/'.test-088-publication/publication.lock'
    storage = base.parent/'.test-088-evidence'
    output = Path(destination).absolute()/'runtime'
    for path in (base/'active.json', lock, storage, output):
        _safe(path)
    publication._require(lock.is_file(), 'evidence_publication_lock_missing')
    with native.device_lock(lock):
        publication._check(cancelled)
        publication._require(not (base/'active.json').exists() or (base/'active.json').is_file(),
                             'evidence_record_invalid')
        record = native._load(base)
        publication._require(record is not None, 'evidence_record_missing')
        paths = _members(base, record)
        notice('保存済みTEST-088の全画像と実行記録を照合しています。対象判定未完の証拠回収です。')
        report_sha = publication._certificate(base, record, cancelled)
        inventory = [('test-088/'+path.relative_to(base).as_posix(), path,
                      *publication._digest(path, cancelled)) for path in paths]
        expected = {base/'active.json': (inventory[0][2], report_sha), paths[1]: (inventory[0][2], report_sha)}
        expected.update({base/('native-'+record['run_id'])/'images'/item['name']: (item['bytes'], item['sha256'])
                         for item in record['images']})
        publication._require(all((size, digest) == expected[path] for _, path, size, digest in inventory),
                             'evidence_source_changed')
        storage.mkdir(mode=0o700, exist_ok=True)
        receipt_path = storage/(record['run_id']+'.receipt.json')
        receipt = _receipt(receipt_path, record)
        local = storage/(record['run_id']+'.zip')
        if receipt is not None:
            publication._require(local.is_file(), 'evidence_archive_missing')
        notice('全画像の照合が完了しました。対象判定未完の証拠ZIPを保存・照合しています。')
        _archive(local, inventory, cancelled)
        signature = publication._digest(local, cancelled)
        value = dict(schema='ngg2-evidence-088-v1', run_id=record['run_id'], report_sha256=report_sha,
                     archive_bytes=signature[0], archive_sha256=signature[1])
        publication._require(receipt is None or receipt == value, 'evidence_receipt_changed')
        output.mkdir(parents=True, exist_ok=True)
        final = output/('test-088-evidence-'+record['run_id']+'.zip')
        _safe(final)
        if not final.exists():
            temporary = final.with_name(final.name+'.'+uuid.uuid4().hex+'.part')
            try:
                publication._copy(local, temporary, cancelled)
                publication._verify_archive(temporary, inventory, cancelled)
                publication._require(publication._digest(temporary, cancelled) == signature, 'evidence_copy_changed')
                publication._check(cancelled)
                _install(temporary, final)
            finally:
                if temporary.exists():
                    temporary.unlink()
        publication._require(final.is_file(), 'evidence_archive_invalid')
        publication._verify_archive(final, inventory, cancelled)
        publication._require(publication._digest(final, cancelled) == signature, 'evidence_destination_changed')
        for _name, source, size, digest in inventory:
            _safe(source)
            publication._require(publication._digest(source, cancelled) == (size, digest), 'evidence_source_changed')
        publication._check(cancelled)
        if receipt is None:
            _safe(receipt_path)
            publication._require(not receipt_path.exists(), 'evidence_receipt_exists')
            native._atomic(receipt_path, json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
        publication._check(cancelled)
        return record, final


def main(argv=None):
    parser = argparse.ArgumentParser(description='保存済みTEST-088の証拠ZIPだけを回収（対象判定未完）')
    parser.parse_args(argv)
    stopped = [False]
    def stop(_signum, _frame):
        stopped[0] = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    def notice(message):
        print(message, flush=True)
    try:
        _record, archive = run(Path.cwd(), cancelled=lambda: stopped[0], notice=notice)
        publication._check(lambda: stopped[0])
        notice('TEST-088: 対象判定未完の証拠ZIPの保存・照合が完了しました。この証拠ZIPは通常の結果保存の完了を示しません。')
        notice('この証拠ZIPを返してください: '+str(archive))
        return 0
    except (ValueError, native.ProbeError, OSError, zipfile.BadZipFile):
        if stopped[0]:
            notice('TEST-088: 証拠回収を取り消しました。端末内の記録を保持しています。')
            return 130
        notice('TEST-088: 証拠回収は未完了です。端末内の記録を保持しています。')
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
