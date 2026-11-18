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
            cycle.closed(params,('run_id','profile','continuous_campaign'),'method_not_allowed')
            cycle.require(cycle.identifier(params['run_id']) and params['profile']==cycle.IRREGULAR_PROTOCOL.profile
                and params['continuous_campaign'] is True,'method_not_allowed')
            return
        if method==cycle.IRREGULAR_PROTOCOL.query and type(params) is dict and params.get('mode')=='campaign_status':
            cycle.closed(params,('run_id','mode','keepalive'),'method_not_allowed')
            cycle.require(cycle.identifier(params['run_id']) and type(params['keepalive']) is bool,'method_not_allowed')
            return
        return super()._validate(method,params)


class FiniteClient116(DeviceClient115):
    trial_revision = DeviceClient116.trial_revision


def main(argv=None):
    parser=argparse.ArgumentParser(description='TEST116: 端末内で連続周回し、停止後に全周を回収')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--until-target',action='store_true')
    mode.add_argument('--recovery',action='store_true')
    parser.add_argument('--python-crypto',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    if args.check:
        print(DeviceClient116.trial_revision+' / '+cycle.API_VERSION);return 0
    spool=Path.home()/'.necroprobe'/'runtime'/'test-116'
    if not args.until_target and not (spool/'continuous-campaign.json').exists() \
            and not (spool/'continuous-campaigns').exists():
        return device_main(argv,test_number='116',protocol_spec=cycle.IRREGULAR_PROTOCOL,client_class=FiniteClient116)
    stopped=[False]
    def stop(_signal,_frame):stopped[0]=True
    previous={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM)}
    notice=lambda text:print(text,flush=True)
    try:
        key,tok=load_pairing(Path.home()/'.loopctrl'/'token.json')
        with OwnedRpcTimer() as timer:
            client=DeviceClient116(HttpTransport(),key,tok,timeout=8,
                crypto=Crypto(native=not args.python_crypto),deadline_owner=timer)
            result=campaign116.run(client,Path.cwd(),spool=spool,
                until_target=args.until_target,recovery_only=args.recovery or not args.until_target,
                cancelled=lambda:stopped[0],notice=notice)
        ledger=result['ledger']
        if not ledger['start_intent']:
            notice('TEST-116: ゲームは開始していません。準備を確認し、同じ通常コマンドを再実行してください。')
        elif ledger['collection_complete'] and not ledger['complete']:
            notice('TEST-116: 診断記録と一覧を保存しました。未確定の記録片は端末に残しています。ゲームの判定完了とは区別します。次の通常実行まで停止します。')
        else:
            notice('TEST-116: '+('全周の保存・照合が完了しました。' if ledger['complete']
                else '回収・照合は未完了です。原本を保持し、--recoveryで回収してください。'))
        notice('停止理由: '+str(result['stop_reason'])+'。')
        if result['campaign_archive'] is not None:
            notice('この返却用ZIPとruntime/test-116-*.zipをすべて送ってください: '+str(result['campaign_archive']))
        return 0 if ledger['collection_complete'] else 2
    except (ProbeError,OSError,ValueError,zipfile.BadZipFile) as error:
        code=error.code if isinstance(error,ProbeError) else 'local_storage_failed'
        notice('TEST-116: 未完了 / '+code+'。原本を保持し、新しいゲームを開始しないでください。');return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)


if __name__=='__main__':
    raise SystemExit(main())
