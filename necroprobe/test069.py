"""TEST069: keep durable checkpoints local and publish a verified result ZIP."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import zipfile

from . import native_walk as native


class PublicationError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise PublicationError(reason)


def _test_label(number):
    _require(type(number) is str and len(number) == 3
        and all('0' <= digit <= '9' for digit in number), 'publication_test_invalid')
    return 'test-'+number


def _check(cancelled):
    _require(not cancelled(), 'cancel_requested')


def _digest(path, cancelled):
    digest = hashlib.sha256()
    size = 0
    _require(not path.is_symlink(), 'publication_symlink')
    with path.open('rb') as handle:
        while True:
            _check(cancelled)
            chunk = handle.read(256*1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def _sync_directory(path):
    directory = os.open(str(path), os.O_RDONLY)
    try:
        try:
            os.fsync(directory)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP, errno.ENOSYS):
                raise
    finally:
        os.close(directory)


def _never_started(record):
    # These are the client's proven preflight/_StartNotSent outcomes. In the
    # latter case start_attempted is durable intent, but no start POST occurred.
    return (record['resolved'] and record['state'] == 'stopped'
            and record['native_state'] is None and record['native_report'] is None
            and not record['images'] and 'image_export' not in record)


def _certificate(base, record, cancelled):
    _check(cancelled)
    report = record['native_report'] or {}
    _require(record['resolved'] and record['start_attempted']
        and record['native_state'] == record['state']
        and native._read_only_terminal(record['native_state'], report),
        'publication_native_incomplete')
    current = record.get('image_export')
    _require(current is not None and record['images'] == current['images'],
        'publication_images_incomplete')
    folder = base/('native-'+record['run_id'])
    for item, offset, prefix in zip(current['images'], current['offsets'], current['prefix_sha256']):
        _require(offset == item['bytes'] and prefix == item['sha256'], 'publication_cursor_incomplete')
        path = folder/'images'/item['name']
        _require(_digest(path, cancelled) == (item['bytes'], item['sha256']), 'publication_image_changed')
        with path.open('rb') as handle:
            header = handle.read(24)
        _require(header[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            and len(header) == 24 and struct.unpack('>II', header[16:24]) == (896,414),
            'publication_image_geometry')
    _require(not (base/'active.json').is_symlink() and not (folder/'report.json').is_symlink(),
        'publication_symlink')
    active = (base/'active.json').read_bytes()
    _require(active == (folder/'report.json').read_bytes()
        and native.json_object(active, 2*1024*1024) == record, 'publication_journal_changed')
    return hashlib.sha256(active).hexdigest()


def _inventory(base, record, cancelled, report_sha, test_number='069'):
    prefix = _test_label(test_number) + '/'
    folder = base/('native-'+record['run_id'])
    _require(folder.is_dir() and not folder.is_symlink(), 'publication_run_missing')
    paths = [base/'active.json']
    for path in sorted(folder.rglob('*')):
        _require(not path.is_symlink(), 'publication_symlink')
        if path.is_file():
            paths.append(path)
        else:
            _require(path.is_dir(), 'publication_special_file')
    inventory = [(prefix+path.relative_to(base).as_posix(), path, *_digest(path, cancelled))
                 for path in paths]
    expected = {prefix+'active.json': report_sha,
        prefix+folder.name+'/report.json': report_sha}
    expected.update({prefix+folder.name+'/images/'+item['name']: item['sha256']
                     for item in record['image_export']['images']})
    actual = {name: digest for name, _path, _size, digest in inventory}
    _require(all(actual.get(name) == digest for name, digest in expected.items()),
        'publication_snapshot_changed')
    return inventory


def _verify_archive(path, inventory, cancelled):
    with zipfile.ZipFile(path) as archive:
        _require(archive.namelist() == [row[0] for row in inventory], 'publication_inventory_changed')
        for name, _source, size, digest in inventory:
            _check(cancelled)
            info = archive.getinfo(name)
            _require(info.file_size == size and info.compress_type == zipfile.ZIP_STORED,
                'publication_inventory_changed')
            actual = hashlib.sha256()
            count = 0
            with archive.open(info) as handle:
                while True:
                    _check(cancelled)
                    chunk = handle.read(256*1024)
                    if not chunk:
                        break
                    actual.update(chunk)
                    count += len(chunk)
            # Reading to EOF also checks every member's ZIP CRC.
            _require((count, actual.hexdigest()) == (size, digest), 'publication_archive_changed')


def _archive(base, record, storage, cancelled, report_sha, test_number='069'):
    inventory = _inventory(base, record, cancelled, report_sha, test_number)
    path = storage/(record['run_id']+'.zip')
    if path.exists():
        _verify_archive(path, inventory, cancelled)
        return path
    temporary = storage/(record['run_id']+'.zip.building')
    _require(not temporary.is_symlink(), 'publication_symlink')
    with temporary.open('wb') as target:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name, source, _size, _sha in inventory:
                _check(cancelled)
                info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                with source.open('rb') as original, archive.open(info, 'w') as entry:
                    while True:
                        _check(cancelled)
                        chunk = original.read(256*1024)
                        if not chunk:
                            break
                        entry.write(chunk)
        target.flush()
        os.fsync(target.fileno())
    _verify_archive(temporary, inventory, cancelled)
    os.replace(temporary, path)
    _sync_directory(storage)
    return path


def _receipt(storage, record):
    path = storage/(record['run_id']+'.receipt.json')
    if not path.exists():
        return None
    _require(not path.is_symlink(), 'publication_symlink')
    with path.open('rb') as handle:
        raw = handle.read(4097)
    _require(len(raw) <= 4096, 'publication_receipt_invalid')
    value = json.loads(raw)
    _require(type(value) is dict and set(value) == {'schema','run_id','report_sha256','archive_sha256','archive_bytes'}
        and value['schema'] == 'ngg2-publication-v1' and value['run_id'] == record['run_id'],
        'publication_receipt_invalid')
    return value


def _published(base, destination, record, storage, cancelled, test_number='069'):
    receipt = _receipt(storage, record)
    final = destination/'runtime'/(_test_label(test_number)+'-'+record['run_id']+'.zip')
    if receipt is None or not final.exists():
        return False
    report_sha = _certificate(base, record, cancelled)
    _require(receipt['report_sha256'] == report_sha, 'publication_receipt_changed')
    _require(_digest(final, cancelled) == (receipt['archive_bytes'], receipt['archive_sha256']),
        'publication_destination_changed')
    archive = _archive(base, record, storage, cancelled, report_sha, test_number)
    _require(_digest(archive, cancelled) == (receipt['archive_bytes'], receipt['archive_sha256']),
        'publication_receipt_changed')
    return True


def _copy(source, target, cancelled):
    _require(not target.is_symlink(), 'publication_symlink')
    with source.open('rb') as original, target.open('wb') as copied:
        while True:
            _check(cancelled)
            chunk = original.read(256*1024)
            if not chunk:
                break
            copied.write(chunk)
        copied.flush()
        os.fsync(copied.fileno())


def _publish(base, destination, record, storage, cancelled, notice, test_number='069', *, prepare=None):
    notice('保存済みの全画像と実行記録を照合しています。')
    report_sha = _certificate(base, record, cancelled)
    # A local assessment belongs to the first immutable archive snapshot.
    # Recovery verifies an existing archive without retrofitting new evidence.
    if prepare is not None and not (storage/(record['run_id']+'.zip')).exists():
        notice('全画像の照合が完了しました。指輪の判定を行います。')
        prepare(base, record, report_sha, cancelled)
        _check(cancelled)
    notice('全画像を確認済みです。返却用ZIPを保存・照合しています。')
    archive = _archive(base, record, storage, cancelled, report_sha, test_number)
    signature = _digest(archive, cancelled)
    output = destination/'runtime'
    output.mkdir(parents=True, exist_ok=True)
    final = output/(_test_label(test_number)+'-'+record['run_id']+'.zip')
    if not final.exists():
        part = final.with_name(final.name+'.part')
        _copy(archive, part, cancelled)
        _require(_digest(part, cancelled) == signature, 'publication_copy_changed')
        _check(cancelled)
        # The spool lock serializes this launcher's writers. Recheck before
        # publication so an unrelated pre-existing artifact is never replaced.
        _require(not final.exists(), 'publication_destination_exists')
        os.replace(part, final)
        _sync_directory(output)
    _require(_digest(final, cancelled) == signature, 'publication_destination_changed')
    value = dict(schema='ngg2-publication-v1', run_id=record['run_id'], report_sha256=report_sha,
        archive_bytes=signature[0], archive_sha256=signature[1])
    native._atomic(storage/(record['run_id']+'.receipt.json'),
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    _check(cancelled)
    return final


def run(destination, *, spool, session, cancelled=lambda: False, notice=print, test_number='069', prepare=None):
    _test_label(test_number)
    _require(prepare is None or callable(prepare), 'publication_prepare_invalid')
    base = Path(spool).resolve()
    destination = Path(destination).resolve()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    storage = base.parent/('.'+base.name+'-publication')
    storage.mkdir(mode=0o700, exist_ok=True)
    # Separate from the device lease held inside native.run_session.
    with native.device_lock(storage/'publication.lock'):
        _check(cancelled)
        record = native._load(base)
        if record is not None and record['resolved'] and not _never_started(record):
            if not _published(base, destination, record, storage, cancelled, test_number):
                notice('前回のZIP保存を再開します。今回はゲームを起動しません。')
                return record, _publish(base, destination, record, storage, cancelled, notice, test_number, prepare=prepare)
        _check(cancelled)
        record = session(base)
        if not isinstance(record, dict):
            raise PublicationError('native_client_incomplete')
        _check(cancelled)
        if not record['resolved'] or _never_started(record):
            return record, None
        _require(record == native._load(base), 'publication_journal_changed')
        return record, _publish(base, destination, record, storage, cancelled, notice, test_number, prepare=prepare)


def main(argv=None, *, test_number='069', prepare=None):
    label = _test_label(test_number)
    heading = 'TEST-'+test_number
    parser = argparse.ArgumentParser(description=heading+': 全画像を永続保存して返却ZIPを作成')
    parser.add_argument('--python-crypto', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.check:
        return native.main(['--check'])
    stopped = [False]
    def stop(_signum, _frame):
        stopped[0] = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    def notice(message):
        print(message, flush=True)
    def session(base):
        options = ['--output', str(base)]
        if args.python_crypto:
            options.append('--python-crypto')
        def outcome(record, cancelled):
            stopped[0] = stopped[0] or cancelled
            return record
        return native.main(options, outcome=outcome, cancelled=lambda: stopped[0])
    try:
        record, archive = run(Path.cwd(), spool=Path.home()/'.necroprobe'/'runtime'/label,
            session=session, cancelled=lambda: stopped[0], notice=notice, test_number=test_number, prepare=prepare)
        _check(lambda: stopped[0])
        report = record['native_report'] or {}
        reason = report.get('reason_name') if record['native_state'] in native.TERMINAL else None
        notice('ゲーム結果: '+record['state']+' / '+(reason or record['stop_reason'] or 'none'))
        if archive is not None:
            notice(heading+': 終了。画像とZIPの保存・照合が完了しました。')
            notice('このZIPを返してください: '+str(archive))
            return 0
        notice(heading+': 結果保存は未完了です。端末内の記録を保持しています。')
        if _never_started(record):
            notice('ゲームの開始要求は送っていません。LoopCtrlのStart Serverと接続を確認して再実行してください。')
        else:
            notice('同じ実行IDを保持しています。ゲームの状態と接続を確認してください。')
        return 2
    except (PublicationError, native.ProbeError, OSError, zipfile.BadZipFile, json.JSONDecodeError):
        notice(heading+': 保存は未完了です。端末内の記録を保持しました。')
        notice('同じフォルダから再実行すると、未完了の処理を先に確認します。')
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
