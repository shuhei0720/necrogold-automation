"""TEST099 ordinary trial, explicit until-target campaign and read-only recovery."""
import argparse
from pathlib import Path
import signal
import zipfile

from . import campaign099 as campaign
from . import native_cycle as cycle
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import HttpTransport, load_pairing
from .trial_evidence099 import TrialClient099
from .validation import ProbeError

REASONS = ('none','goods','cancelled','foreground','locked','owner_paused','capture','stale',
           'beat','late','movement','unknown_input','no_path','partial_goods','limit','session',
           'restart','screen','generation','heartbeat','geometry')


def main(argv=None):
    parser=argparse.ArgumentParser(description='TEST099: 通常試験と安全な有限run連続試運転')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--until-target',action='store_true',help='正常な区切りだけ自動で次runへ進む')
    mode.add_argument('--recovery',action='store_true',help='前runの回収だけを行い新startを禁止する')
    parser.add_argument('--python-crypto',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    if args.check:
        print('native-trial-v1 / '+cycle.API_VERSION)
        return 0
    cancelled=[False]
    def stop(_signal,_frame):cancelled[0]=True
    previous={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM)}
    notice=lambda text:print(text,flush=True)
    try:
        key,tok=load_pairing(Path.home()/'.loopctrl'/'token.json')
        with OwnedRpcTimer() as timer:
            client=TrialClient099(HttpTransport(),key,tok,timeout=8,
                crypto=Crypto(native=not args.python_crypto),deadline_owner=timer)
            result=campaign.run(client,Path.cwd(),spool=Path.home()/'.necroprobe'/'runtime'/'test-099',
                until_target=args.until_target,recovery_only=args.recovery,
                cancelled=lambda:cancelled[0],notice=notice)
        ledger=result['ledger'];reason=result['stop_reason']
        if reason=='trial_support_missing':
            notice('TEST-099: 新IPAの試運転機能を確認できません。IPAを更新してください。ゲームは開始していません。')
        elif reason in ('target','candidate'):
            last=ledger['runs'][-1]
            text='のろいのゆびわを確認' if reason=='target' and last['assessment_adopted'] else 'のろいのゆびわの候補を保持'
            notice('対象判定: '+text+'。次のrunは開始しません。')
        elif ledger['runs']:
            last=ledger['runs'][-1];native=last['controller_reason']
            label=REASONS[native] if type(native) is int and 0<=native<len(REASONS) else 'unclassified'
            notice('自動操作の停止: '+label+' / '+reason+'。対象なしの確認とは区別します。')
        if ledger['state']=='pending':
            if result['record'] is not None and result['record']['start_intent']:
                notice('TEST-099: 回収は未完了です。同じrunと記録を保持しています。--recoveryで回収してください。')
            else:
                notice('TEST-099: ゲームは開始していません。準備を確認して通常コマンドを再実行してください。')
        else:
            notice('TEST-099: 停止後の全画像・実行記録・run ZIPの保存と照合が完了しました。')
        if result['campaign_archive'] is not None:
            notice('この返却用ZIPを送ってください: '+str(result['campaign_archive']))
        else:
            notice('TEST-099: 全run ZIP未検証のため返却用ZIPはまだ作成していません。記録を保持しています。')
        return 2 if ledger['state']=='pending' else 0
    except (ProbeError,OSError,ValueError,zipfile.BadZipFile) as error:
        reason=error.code if isinstance(error,ProbeError) else 'local_storage_failed'
        notice('TEST-099: 未完了 / '+reason+'。元の記録は削除せず、新しいゲームを開始しないでください。')
        return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)


if __name__=='__main__':raise SystemExit(main())
