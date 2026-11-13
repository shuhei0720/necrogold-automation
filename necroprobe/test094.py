"""TEST094: native goods recognition and consecutive, evidenced shop cycles."""
import argparse
from pathlib import Path
import signal
import zipfile

from . import native_cycle as cycle
from .cycle_publication import run
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import HttpTransport, load_pairing
from .validation import ProbeError


def _assessments(base, record):
    results = []
    for item in record['records']:
        if item['kind'] not in ('assessment', 'checkpoint'):
            continue
        raw = cycle._read(base/('cycle-'+record['run_id'])/'records'/cycle.record_name(item), cycle.MAX_RECORD)
        body = cycle.json_object(raw, cycle.MAX_RECORD)
        payload = body.get('payload', {})
        assessment = payload.get('assessment', payload) if type(payload) is dict else {}
        if type(assessment) is dict and assessment.get('outcome') in ('target', 'candidate', 'negative', 'unknown'):
            status = assessment.get('status', 'ok')
            if status not in ('ok', 'cancelled', 'deadline', 'invalid', 'allocation', 'kernel'):
                status = 'invalid'
            results.append((item['cycle'], assessment['outcome'], status))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='TEST094: 端末内の商品判定と自動周回')
    parser.add_argument('--python-crypto', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.check:
        print(cycle.REVISION+' / '+cycle.API_VERSION)
        return 0
    cancelled = [False]
    def stop(_signal, _frame):
        cancelled[0] = True
    previous = {sig:signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    notice = lambda message: print(message, flush=True)
    base = Path.home()/'.necroprobe'/'runtime'/'test-094'
    try:
        key, tok = load_pairing(Path.home()/'.loopctrl'/'token.json')
        with OwnedRpcTimer() as timer:
            client = cycle.CycleClient(HttpTransport(), key, tok, timeout=8,
                crypto=Crypto(native=not args.python_crypto), deadline_owner=timer)
            record, archive = run(client, Path.cwd(), spool=base,
                cancelled=lambda:cancelled[0], notice=notice)
        if archive is None:
            reason = record['last_error'] or 'native_result_pending'
            notice('TEST-094: 未完了 / '+reason+'。同じ実行IDを保持しています。')
            if reason == 'cycle_notification_permission':
                notice('ゲームは開始していません。LoopCtrlを開き、通知を許可してから実行してください。')
            else:
                notice('このフォルダの記録を残してください。未回収のまま新しいゲームは開始しません。')
            return 2
        assessments = _assessments(base, record)
        if not assessments:
            notice('対象判定: 未実施（商品判定用の記録なし）。対象なしの確認ではありません。')
        for cycle_id, outcome, status in assessments:
            text = {'target':'のろいのゆびわを確認', 'candidate':'のろいのゆびわ候補を保持',
                'negative':'陳列品に対象なしを確認（宝箱は対象外）',
                'unknown':'判定実施・未確定のため保持'}[outcome]
            if status != 'ok':
                text = '判定未完了 / '+status+'。対象なしとは扱いません。'
            notice('商店判定 '+str(cycle_id)+': '+text)
        manifest = cycle.verify_evidence(base, record)
        if manifest['interrupted'] or not manifest['complete']:
            notice('TEST-094: 中断・不完全な実行の診断記録です。正常な商品確認完了には数えません。')
        notice('TEST-094: 終了。全画像・実行記録とZIPの保存・照合が完了しました。')
        notice('このZIPを返してください: '+str(archive))
        return 0
    except (ProbeError, OSError, ValueError, zipfile.BadZipFile) as exc:
        reason = exc.code if isinstance(exc, ProbeError) else 'local_storage_failed'
        notice('TEST-094: 保存は未完了 / '+reason+'。端末内の同じ実行IDと記録を保持しました。')
        notice('全画像・ZIPの照合前に完了とは扱いません。')
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
