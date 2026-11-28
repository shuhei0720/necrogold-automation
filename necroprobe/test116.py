"""TEST116 continuous native campaigns, ordinary finite trial, and recovery."""
import argparse
from pathlib import Path
import signal
import zipfile

from . import campaign116
from . import native_cycle as cycle
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import HttpTransport, load_pairing
from .test099 import main as device_main
from .test115 import DeviceClient115
from .validation import ProbeError


class DeviceClient116(DeviceClient115):
    trial_revision = 'native-device-failures-trial-v116'
    yield_after_restart = False
    allow_restarted_budget = False
    required_capabilities = DeviceClient115.required_capabilities | frozenset((campaign116.CAPABILITY,))

    def _validate(self, method, params):
        if method=='necro_native_start':
            initial=cycle.initial_restart_enabled(self)
            cycle.closed(params,('run_id','profile','continuous_campaign')
                + (('initial_restart',) if initial else ()),'method_not_allowed')
            cycle.require(cycle.identifier(params['run_id']) and params['profile']==cycle.IRREGULAR_PROTOCOL.profile
                and params['continuous_campaign'] is True
                and (not initial or params['initial_restart'] is True),'method_not_allowed')
            return
        if method==cycle.IRREGULAR_PROTOCOL.query and type(params) is dict and params.get('mode')=='campaign_status':
            cycle.closed(params,('run_id','mode','keepalive'),'method_not_allowed')
            cycle.require(cycle.identifier(params['run_id']) and type(params['keepalive']) is bool,'method_not_allowed')
            return
        return super()._validate(method,params)


class FiniteClient116(DeviceClient115):
    trial_revision = DeviceClient116.trial_revision


def _main(argv, *, test_number, continuous_client, finite_client):
    campaign116._number(test_number)
    banner='TEST-'+test_number
    parser=argparse.ArgumentParser(description='TEST'+test_number+': 端末内で連続周回し、停止後に全周を回収')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--until-target',action='store_true')
    mode.add_argument('--recovery',action='store_true')
    parser.add_argument('--python-crypto',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    if args.check:
        print(continuous_client.trial_revision+' / '+cycle.API_VERSION);return 0
    spool=Path.home()/'.necroprobe'/'runtime'/('test-'+test_number)
    if not args.until_target and not (spool/'continuous-campaign.json').exists() \
            and not (spool/'continuous-campaigns').exists():
        return device_main(argv,test_number=test_number,protocol_spec=cycle.IRREGULAR_PROTOCOL,client_class=finite_client)
    stopped=[False]
    def stop(_signal,_frame):stopped[0]=True
    previous={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM)}
    notice=lambda text:print(text,flush=True)
    if (test_number in ('125','126') and args.until_target
            and getattr(continuous_client,'wait_for_startup_ready',False) is True):
        notice(banner+': 起動準備修正1。保存記録と通知の準備完了を確認してから開始します。')
    try:
        key,tok=load_pairing(Path.home()/'.loopctrl'/'token.json')
        with OwnedRpcTimer() as timer:
            client=continuous_client(HttpTransport(),key,tok,timeout=8,
                crypto=Crypto(native=not args.python_crypto),deadline_owner=timer)
            result=campaign116.run(client,Path.cwd(),spool=spool,
                test_number=test_number,
                until_target=args.until_target,recovery_only=args.recovery or not args.until_target,
                cancelled=lambda:stopped[0],notice=notice)
        ledger=result['ledger']
        admission_detail=(campaign116.admission.EXPLANATIONS.get(result['stop_reason'])
            if test_number=='126' and getattr(continuous_client,'start_admission_diagnostics',False) is True
            and not ledger['start_intent'] else None)
        if not ledger['start_intent']:
            notice(banner+': ゲームは開始していません。'+('開始を拒否した条件を確認してください。'
                if admission_detail is not None else '準備を確認し、同じ通常コマンドを再実行してください。'))
        elif ledger['collection_complete'] and not ledger['complete']:
            notice(banner+': 診断記録と一覧を保存しました。未確定の記録片は端末に残しています。ゲームの判定完了とは区別します。次の通常実行まで停止します。')
        else:
            notice(banner+': '+('全周の保存・照合が完了しました。' if ledger['complete']
                else '回収・照合は未完了です。原本を保持し、--recoveryで回収してください。'))
        notice('停止理由: '+str(result['stop_reason'])+'。')
        if admission_detail is not None:
            notice('開始できない理由: '+admission_detail)
            notice('記録は削除せず、この停止理由と説明が見える画面を送ってください。')
        if result['campaign_archive'] is not None:
            notice('この返却用ZIPとruntime/test-'+test_number+'-*.zipをすべて送ってください: '+str(result['campaign_archive']))
        return 0 if ledger['collection_complete'] else 2
    except (ProbeError,OSError,ValueError,zipfile.BadZipFile) as error:
        code=error.code if isinstance(error,ProbeError) else 'local_storage_failed'
        notice(banner+': 未完了 / '+code+'。原本を保持し、新しいゲームを開始しないでください。')
        if test_number in ('125','126'):
            explanation={
                'cycle_recovery_scan_pending':'保存記録の確認が開始期限内に終わりませんでした。LoopCtrlと記録をそのまま保ち、起動診断JSONを送ってください。',
                'cycle_recovery_scan_failed':'保存記録の確認に失敗しました。記録は削除せず、起動診断JSONを送ってください。',
                'cycle_notification_pending':'通知の許可状態を開始期限内に確認できませんでした。起動診断JSONを送ってください。',
                'cycle_prepare_timeout':'起動準備の応答が元の開始期限を越えました。ゲーム開始要求は送っていません。',
                'cycle_prepare_not_ready':'準備完了を確認できませんでした。ゲーム開始要求は送っていません。',
            }.get(code)
            if explanation is not None:notice(explanation)
        return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)


def main(argv=None):
    return _main(argv,test_number='116',continuous_client=DeviceClient116,finite_client=FiniteClient116)


if __name__=='__main__':
    raise SystemExit(main())
