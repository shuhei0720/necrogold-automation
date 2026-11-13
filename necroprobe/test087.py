"""TEST087 device entry; reuse verified local result publication."""
import time

from .test069 import main as device_main
from .target_assessment import AssessmentError, prepare_assessment
from .ring_status import assessment_label


_ENGINE_FAILURES = frozenset((
    'ring_native_cache', 'ring_native_cancelled', 'ring_native_child',
    'ring_native_elf', 'ring_native_failed', 'ring_native_input',
    'ring_native_integrity', 'ring_native_manifest', 'ring_native_output',
    'ring_native_reply', 'ring_native_schema', 'ring_native_symlink',
    'ring_native_timeout', 'ring_python_version', 'ring_early_changed', 'ring_early_failed'))


def _prepare(base, record, report_sha, cancelled, *, classify=None, before=None):
    started = time.monotonic()
    next_notice = [started+5]
    print('指輪判定中。商品画像の有無と保存状態を確認しています。', flush=True)
    def checked_cancel():
        stopped = cancelled()
        if not stopped:
            now = time.monotonic()
            if now >= next_notice[0]:
                print('指輪判定中（経過'+str(int(now-started))+'秒）。', flush=True)
                next_notice[0] = now+5
        return stopped
    try:
        if before is not None:
            before(record)
        if classify is None:
            value = prepare_assessment(base, record, report_sha, checked_cancel)
        else:
            value = prepare_assessment(base, record, report_sha, checked_cancel, classify=classify)
    except AssessmentError as error:
        reason = str(error)
        if reason in _ENGINE_FAILURES:
            print('指輪判定を完了できませんでした（'+reason+'）。元データを保持します。', flush=True)
        raise
    label = assessment_label(value['outcome'], has_sources=bool(value['sources']))
    print('対象判定: '+label, flush=True)
    return value


def main(argv=None):
    return device_main(argv, test_number='087', prepare=_prepare)


if __name__ == '__main__':
    raise SystemExit(main())
