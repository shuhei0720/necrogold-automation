"""Publish the already saved TEST087 result without starting a device session."""
import argparse
from pathlib import Path
import signal
import zipfile

from . import native_walk as native
from . import test069 as publication, test087


def run(destination, *, cancelled=lambda: False, notice=print):
    base = Path.home()/'.necroprobe'/'runtime'/'test-087'
    storage = base.parent/'.test-087-publication'
    publication._require(not base.is_symlink() and not storage.is_symlink(),
                         'publication_symlink')
    storage.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = Path(destination).resolve()
    with native.device_lock(storage/'publication.lock'):
        publication._check(cancelled)
        record = native._load(base)
        publication._require(record is not None, 'recovery_record_missing')
        publication._require(record['resolved'] and not publication._never_started(record),
                             'publication_native_incomplete')
        if publication._published(base, destination, record, storage, cancelled, '087'):
            notice('保存済みZIPと元の記録の一致を確認しました。')
            return record, destination/'runtime'/('test-087-'+record['run_id']+'.zip')
        publication._check(cancelled)
        notice('保存済みTEST-087の対象判定とZIP保存を再開します。')
        return record, publication._publish(base, destination, record, storage,
            cancelled, notice, test_number='087', prepare=test087._prepare)


def main(argv=None):
    parser = argparse.ArgumentParser(description='保存済みTEST-087の判定・ZIP保存だけを回復')
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
        notice('TEST-087: 保存済み結果の確認とZIP保存が完了しました。')
        notice('このZIPを返してください: '+str(archive))
        return 0
    except (ValueError, native.ProbeError, OSError, zipfile.BadZipFile) as error:
        if stopped[0]:
            notice('TEST-087: 回復を取り消しました。端末内の記録を保持しています。')
            return 130
        if str(error) == 'recovery_record_missing':
            notice('TEST-087: 保存済みの実行記録が見つかりません。既存データを保持しています。')
        else:
            notice('TEST-087: 記録・画像の保存が未完了か、照合できません。端末内の記録を保持しています。')
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
