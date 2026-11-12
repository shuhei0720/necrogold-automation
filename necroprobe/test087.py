"""TEST087 device entry; reuse verified local result publication."""
import time

from .test069 import main as device_main
from .target_assessment import prepare_assessment


def _prepare(base, record, report_sha, cancelled):
    started = time.monotonic()
    next_notice = [started+5]
    print('指輪判定中。保存済みの画像を確認しています。', flush=True)
    def checked_cancel():
        stopped = cancelled()
        if not stopped:
            now = time.monotonic()
            if now >= next_notice[0]:
                print('指輪判定中（経過'+str(int(now-started))+'秒）。', flush=True)
                next_notice[0] = now+5
        return stopped
    value = prepare_assessment(base, record, report_sha, checked_cancel)
    label = {'target': 'のろいのゆびわ（アイコンと名前が一致）',
             'candidate': '指輪候補（保持して目視確認してください）',
             'unknown': '不明（判定できる証拠が不足しています）'}[value['outcome']]
    print('対象判定: '+label, flush=True)
    return value


def main(argv=None):
    return device_main(argv, test_number='087', prepare=_prepare)


if __name__ == '__main__':
    raise SystemExit(main())
