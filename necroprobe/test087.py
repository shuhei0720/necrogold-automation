"""TEST087 device entry; reuse verified local result publication."""
from .test069 import main as device_main
from .target_assessment import prepare_assessment


def _prepare(base, record, report_sha, cancelled):
    value = prepare_assessment(base, record, report_sha, cancelled)
    label = {'target': 'のろいのゆびわ（アイコンと名前が一致）',
             'candidate': '指輪候補（保持して目視確認してください）',
             'unknown': '不明（判定できる証拠が不足しています）'}[value['outcome']]
    print('対象判定: '+label, flush=True)
    return value


def main(argv=None):
    return device_main(argv, test_number='087', prepare=_prepare)


if __name__ == '__main__':
    raise SystemExit(main())
